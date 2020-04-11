local PythonVersion(pyversion="3.5") = {
    name: "python" + std.strReplace(pyversion, '.', '') + "-pytest",
    image: "python:" + pyversion,
    pull: "always",
    environment: {
        PY_COLORS: 1
    },
    commands: [
        "pip install -r dev-requirements.txt -qq",
        "pip install -qq .",
        "git-batch --help",
    ],
    depends_on: [
        "clone",
    ],
};

local PipelineLint = {
    kind: "pipeline",
    name: "lint",
    platform: {
        os: "linux",
        arch: "amd64",
    },
    steps: [
        {
            name: "flake8",
            image: "python:3.8",
            pull: "always",
            environment: {
                PY_COLORS: 1
            },
            commands: [
                "pip install -r dev-requirements.txt -qq",
                "pip install -qq .",
                "flake8 ./gitbatch",
            ],
        },
    ],
    trigger: {
        ref: ["refs/heads/master", "refs/tags/**", "refs/pull/**"],
    },
};

local PipelineTest = {
    kind: "pipeline",
    name: "test",
    platform: {
        os: "linux",
        arch: "amd64",
    },
    steps: [
        PythonVersion(pyversion="3.5"),
        PythonVersion(pyversion="3.6"),
        PythonVersion(pyversion="3.7"),
        PythonVersion(pyversion="3.8"),
    ],
    trigger: {
        ref: ["refs/heads/master", "refs/tags/**", "refs/pull/**"],
    },
    depends_on: [
        "lint",
    ],
};

local PipelineSecurity = {
    kind: "pipeline",
    name: "security",
    platform: {
        os: "linux",
        arch: "amd64",
    },
    steps: [
        {
            name: "bandit",
            image: "python:3.8",
            pull: "always",
            environment: {
                PY_COLORS: 1
            },
            commands: [
                "pip install -r dev-requirements.txt -qq",
                "pip install -qq .",
                "bandit -r ./gitbatch -x ./gitbatch/tests",
            ],
        },
    ],
    depends_on: [
        "test",
    ],
    trigger: {
        ref: ["refs/heads/master", "refs/tags/**", "refs/pull/**"],
    },
};

local PipelineBuildContainer(arch="amd64") = {
  kind: "pipeline",
  name: "build-container-" + arch,
  platform: {
    os: "linux",
    arch: arch,
  },
  steps: [
    {
      name: "build",
      image: "python:3.8",
      pull: "always",
      commands: [
          "python setup.py bdist_wheel",
      ]
    },
    {
      name: "dryrun",
      image: "plugins/docker:18-linux-" + arch,
      pull: "always",
      settings: {
        dry_run: true,
        dockerfile: "Dockerfile",
        repo: "xoxys/git-batch",
        username: { "from_secret": "docker_username" },
        password: { "from_secret": "docker_password" },
      },
      when: {
        ref: ["refs/pull/**"],
      },
    },
    {
      name: "publish",
      image: "plugins/docker:18-linux-" + arch,
      pull: "always",
      settings: {
        auto_tag: true,
        auto_tag_suffix: arch,
        dockerfile: "Dockerfile",
        repo: "xoxys/git-batch",
        username: { "from_secret": "docker_username" },
        password: { "from_secret": "docker_password" },
      },
      when: {
          ref: ["refs/heads/master", "refs/tags/**"],
      },
    },
  ],
  depends_on: [
    "security",
  ],
  trigger: {
      ref: ["refs/heads/master", "refs/tags/**", "refs/pull/**"],
  },
};

local PipelineNotifications = {
  kind: "pipeline",
  name: "notifications",
  platform: {
    os: "linux",
    arch: "amd64",
  },
  steps: [
    {
      image: "plugins/manifest",
      name: "manifest",
      pull: "always",
      settings: {
        ignore_missing: true,
        auto_tag: true,
        username: { from_secret: "docker_username" },
        password: { from_secret: "docker_password" },
        spec: "manifest.tmpl",
      },
      when: {
        ref: [
          'refs/heads/master',
          'refs/tags/**',
        ],
      },
    },
    {
      name: "readme",
      image: "sheogorath/readme-to-dockerhub",
      pull: "always",
      environment: {
        DOCKERHUB_USERNAME: { from_secret: "docker_username" },
        DOCKERHUB_PASSWORD: { from_secret: "docker_password" },
        DOCKERHUB_REPO_PREFIX: "xoxys",
        DOCKERHUB_REPO_NAME: "git-batch",
        README_PATH: "README.md",
        SHORT_DESCRIPTION: "git-batch"
      },
      when: {
        ref: [
          'refs/heads/master',
          'refs/tags/**',
        ],
      },
    },
    {
      name: "microbadger",
      image: "plugins/webhook",
      pull: "always",
      settings: {
        urls: { from_secret: "microbadger_url" },
      },
    },
    {
      name: "matrix",
      image: "plugins/matrix",
      settings: {
        template: "Status: **{{ build.status }}**<br/> Build: [{{ repo.Owner }}/{{ repo.Name }}]({{ build.link }}) ({{ build.branch }}) by {{ build.author }}<br/> Message: {{ build.message }}",
        roomid: { "from_secret": "matrix_roomid" },
        homeserver: { "from_secret": "matrix_homeserver" },
        username: { "from_secret": "matrix_username" },
        password: { "from_secret": "matrix_password" },
      },
      when: {
        status: [ "success", "failure" ],
      },
    },
  ],
  depends_on: [
    "build-container-amd64",
    "build-container-arm64",
    "build-container-arm"
  ],
  trigger: {
    ref: ["refs/heads/master", "refs/tags/**"],
    status: [ "success", "failure" ],
  },
};

[
    PipelineLint,
    PipelineTest,
    PipelineSecurity,
    PipelineBuildContainer(arch="amd64"),
    PipelineBuildContainer(arch="arm64"),
    PipelineBuildContainer(arch="arm"),
    PipelineNotifications,
]
