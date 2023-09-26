# application-template python 

## Usage 

### Create new application repo

Create new application repo using `application-template` include-all branches

Please give a meaningful name to the repo keeping in mind that repo name will be a part of your applications URL as a subdomain 

**examples**:  
`mexico-invoice` >> [https://mexico-invoice.app-integrations.cloudbeds-dev.com](https://mexico-invoice.app-integrations.cloudbeds-dev.com)  
`<repo-name>` >> [https://<repo-name>.app-integrations.cloudbeds-dev.com](https://<repo-name>.app-integrations.cloudbeds-dev.com)

Please do not add any kind of useless suffixes such as `-service`, `-integration`, `-deployment` or similar, but keep it short and clear. 

### Checkout language template 

Template repo contains multiple branches, so checkout corresponding branch that is the best match for your application.   

### Examine repo content

Get familiar with repo structure and please do not change base dirs unless you have a good reason to do so and you understand all implications.

The template repo usually contains following dirs: 

* `.github` GitHub action workflows used to provide CI/CD functionality 
* `_argocd` ArgoCD deployment manifests and application helm chart and its environment specific values
* `docker`  Place for `.Dockerfile(s)` and its dependencies. If multiple docker images are required to be build please use sub folders 
for each image with clear names such as `nginx` , `flask` and so on    
* `src` application source code dir

### Update template files
Templates provide good starting point for your source code but feel free to start from scratch if desired  

ArgoCD deployment template should be updated, replacing all placeholders `<repo-name>` in all files of `_argocd` dir with your actual repo name.

Rename helm chart dir `_argocd/repo-name` to your repo name as well.

The same way update deployment manifest files the same way `_argocd/applications/dev/repo-name.yaml.tpl` replacing `repo-name` with your actual repo name.

### Ready to code and build

Once above steps are complete you are ready to go. 

At this point you can update your app source code and ensure docker-compose file up to date and works on your local machine. 

Commit your changes and open a PR to merge your changes to `main` branch.

Once your changes are merged GitHub actions will start a workflow to build your docker image(s) and push them to GitHub Container Registry, 

### ArgoCD project bootstrap  
Once build and push process are successful, and you have tested your code locally, please request ArgoCD project.

After you've got a confirmation that your ArgoCD project has been bootstrapped please validate you have access to [ArgoCD UI](https://argocd.app-integrations.cloudbeds-dev.com/) 

Change `deployemnt` Job conditional to `true` in [.github/workflows/merge-main.yaml#L49](.github/workflows/merge-main.yaml#L49) 

Rename deployment file `_argocd/applications/dev/repo-name.yaml.tpl` by removing extension `.tpl` 

Once those changes are merged to `main` it will take 2-3 min for ArgoCD to detect changes and deployment process will start.
