{
  description = "oddship.net website";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
      in
      {
        packages.default = pkgs.buildNpmPackage {
          pname = "oddship-site";
          version = "1.0.0";
          src = ./.;
          npmDepsHash = "sha256-s4kTf27yNgS0Ukt//WVmfjD/+/cATGy4iIv3b+Z+TbI=";
          buildPhase = ''
            npm run build
          '';
          installPhase = ''
            cp -r dist $out
          '';
        };

        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            nodejs_20
            nodePackages.npm
          ];
        };
      });
}
