{
  description = "Globus sync helper development environment";

  inputs.nixpkgs.url = "https://flakehub.com/f/NixOS/nixpkgs/0.1.*.tar.gz";

  outputs = {
    self,
    nixpkgs,
  }: let
    supportedSystems = ["x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin"];
    forEachSupportedSystem = f:
      nixpkgs.lib.genAttrs supportedSystems (system:
        let
          pkgs = import nixpkgs {inherit system;};

          pythonVersion = "3.13";
          concatMajorMinor = v:
            pkgs.lib.pipe v [
              pkgs.lib.versions.splitVersion
              (pkgs.lib.sublist 0 2)
              pkgs.lib.concatStrings
            ];
          python = pkgs."python${concatMajorMinor pythonVersion}";
          pythonPackages = pkgs."python${concatMajorMinor pythonVersion}Packages";

          globusSyncHelper = pythonPackages.buildPythonPackage {
            pname = "globus-sync-helper";
            version = "0.1.0";
            src = ./.;
            format = "pyproject";
            nativeBuildInputs = with pythonPackages; [
              setuptools
              wheel
            ];
            propagatedBuildInputs = with pythonPackages; [
              click
            ];
            pythonImportsCheck = [
              "globus_helper"
              "globus_helper.main"
              "globus_helper.transfer.main"
            ];
          };

          pythonEnv = python.withPackages (_ps: [
            globusSyncHelper
            pythonPackages.pytest
            pythonPackages.ipykernel
          ]);
        in
        f {
          inherit pkgs python pythonPackages globusSyncHelper pythonEnv;
        });
  in {
    packages = forEachSupportedSystem ({
      globusSyncHelper,
      pythonEnv,
      ...
    }: {
      default = globusSyncHelper;
      python = pythonEnv;
    });

    apps = forEachSupportedSystem ({
      pythonEnv,
      ...
    }: {
      default = {
        type = "app";
        program = "${pythonEnv}/bin/python";
      };
      globus-helper = {
        type = "app";
        program = "${pythonEnv}/bin/globus-helper";
      };
    });

    devShells = forEachSupportedSystem ({
      pkgs,
      python,
      pythonEnv,
      globusSyncHelper,
      ...
    }: {
      default = pkgs.mkShell {
        packages = [
          pythonEnv
          globusSyncHelper
          pkgs.git
          pkgs.globus-cli
        ];

        shellHook = ''
          export PYTHONNOUSERSITE=1
          alias globus-helper="${pythonEnv}/bin/globus-helper"
          echo "Loaded globus-sync-helper dev environment (Python ${python.version})."
        '';

        postShellHook = ''
          KERNEL_NAME="globus-sync-helper-${python.version}"
          KERNEL_DIR="$HOME/.local/share/jupyter/kernels/$KERNEL_NAME"
          if [ ! -d "$KERNEL_DIR" ]; then
            python -m ipykernel install --user \
              --name "$KERNEL_NAME" \
              --display-name "Python ${python.version} (flake)" >/dev/null
          fi
        '';
      };
    });
  };
}
