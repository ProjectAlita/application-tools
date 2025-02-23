### Guide for GitHub OAuth App

- Create a new OAuth App: 
GitHub > Settings > Developer Settings > OAuth Apps
https://github.com/settings/developers

- Install `gh` on your local machine
MacOS:
```bash
brew install gh
```

- Log in GitHub using `project` scope:
MacOS:
```bash
gh auth login --scopes "project"
```

- Get auth token:
MacOS:
```bash
gh auth token
```