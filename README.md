# Judge Queuer
This repository contains the code that is run on the Judge Queuer, which is responsible for delegating tasks to Judge Runners, and spinning up new machines if needed.

This is a Python 3.12 repository, with the main entrypoint file being `judgequeuer.py`.

For development, a virtual environment is recommended. You can install dependencies with `pip install -r requirements.txt`.

## Azure setup
You need to create a `.env` file according to the following template:
```
AZURE_SUBSCRIPTION_ID = "43d25139-b8b0-497c-9acf-9af450da2d53"
AZURE_RESOURCE_GROUP_NAME = "judge-queuer"
AZURE_NSG_NAME = "judge-queuer-nsg"
AZURE_VNET_NAME = "judge-queuer-vnet"
AZURE_VNET_SUBNET_NAME = "default"
AZURE_VMAPP_RESOURCE_GROUP = "BenchLab"
AZURE_VMAPP_GALLERY = "runner_container_gallery"
AZURE_VMAPP_NAME = "runner_container_application"
AZURE_VMAPP_VERSION = "latest"
```

To find your subscription ID, go to the Subscriptions page on the Azure portal. Here, select the subscription which you want the system to operate under, and it will say the Subscription ID at the top of the page.

For the Resource Group name, you can make a new resource group for working on this repository. Go to the 'Resource groups' page on teh Azure portal, hit create and fill in a name and region. I recommend a region close to you, e.g. UK South if you're in the Netherlands. Additionally, make sure the Virtual Machine prices in that region are not too expensive, as the location of the VMs will (likely) be determined by the location of the resource group.

Go to the Network Security Groups page, and create a new NSG with a name of your choosing, which you should add to the `.env` file as 'AZURE_NSG_NAME'. Make sure you add it to the right resource group and region.

Go to the Virtual Networks page, and create a new Vnet with a name (which you should add to the 'AZURE_VNET_NAME' in the `.env` file). Most settings can be left at the default. If you do change the subnet name, make sure you change the corresponding 'AZURE_VNET_SUBNET_NAME' in `.env`.

Furthermore, you need to import some settings that were used to create the VM Application on the Judge Runner side. This are filled into the `.env` file under `AZURE_VMAPP_...`, and you should use the same values as defined when creating the VM Application.

Note that all values of the `.env` file filled in above are good for the current development setup.

### Azure Authentication
You need to somehow provide authentication for your Azure instance. See [Azure Python SDK documentation](https://learn.microsoft.com/en-us/python/api/azure-identity/azure.identity.defaultazurecredential?view=azure-python) for the available options in this regard.

The way I set it up, was by installing the Azure CLI tool (option 5 on the list from the docs page mentioned above). 
With the CLI tool, you can use `az login` to log in to your Microsoft account. 
After this, you can run the script as you wish.
Note that this option for authentication is only good for development and testing, and should not be used for production.

If you already had your IDE open with this project, you may have to restart it to make the IDE use the Azure credentials properly.

## Formatting
For proper code formatting, we use Ruff. When you create a pull request, Ruff automatically checks the code and tells you about any possible formatting errors.

If you want to use Ruff locally, install it with `pip install ruff`, then use `ruff check` to check for errors.

Furthermore, please use the [EditorConfig for VS Code extension](https://marketplace.visualstudio.com/items?itemName=EditorConfig.EditorConfig) if you use VS Code. This automatically sets up your IDE for this repository with the right formatting (e.g. indentation) settings.
