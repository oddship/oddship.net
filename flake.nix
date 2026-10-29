{
  description = "Oddship project showcase";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-26.05";
    flake-utils.url = "github:numtide/flake-utils";
    doordarshan = {
      url = "github:oddship/doordarshan-zola/b45a5d5421eb7a2dfcb5f5e081ac5b3dc04d1c5c";
      flake = false;
    };
  };

  outputs = { self, nixpkgs, flake-utils, doordarshan }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        zola = assert pkgs.lib.assertMsg (pkgs.lib.versionOlder pkgs.zola.version "0.23")
          "Doordarshan requires Zola with Tera 1; validate a theme migration before using Zola 0.23+.";
          pkgs.zola;
      in
      {
        packages.default = pkgs.stdenv.mkDerivation {
          pname = "oddship-site";
          version = "1.0.0";
          src = ./.;
          nativeBuildInputs = [ zola pkgs.python3 ];
          SSL_CERT_FILE = "${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt";
          buildPhase = ''
            rm -rf themes/doordarshan
            mkdir -p themes
            cp -R ${doordarshan} themes/doordarshan
            chmod -R u+w themes/doordarshan
            zola build
            printf '%s\n' "${self.rev or self.dirtyRev or "unknown"}" > public/revision.txt
          '';
          doCheck = true;
          checkPhase = ''
            python scripts/check_site.py --site public
            python -m unittest discover -s tests -v
          '';
          installPhase = ''
            cp -r public $out
          '';
        };

        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            zola
            git
            python3
            nodejs_24
            yarn
            just
            playwright-driver
          ];

          shellHook = ''
            export PLAYWRIGHT_BROWSERS_PATH="${pkgs.playwright-driver.browsers}"
            export PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=true

            echo "Development environment loaded!"
            echo "Available tools:"
            echo "  - Zola: $(zola --version)"
            echo "  - Just: $(just --version)"
            echo ""
            echo "Zola commands:"
            echo "  zola serve - Start development server"
            echo "  zola build - Build site for production"
            echo "  zola init <new-site> - Create new site"
          '';
        };

        # A silent shell for MCP servers (avoids breaking JSON-RPC with stdout noise)
        devShells.mcp = pkgs.mkShell {
          buildInputs = with pkgs; [
            nodejs_24
            playwright-driver
          ];

          shellHook = ''
            export PLAYWRIGHT_BROWSERS_PATH="${pkgs.playwright-driver.browsers}"
            export PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=true
          '';
        };
      });
}
