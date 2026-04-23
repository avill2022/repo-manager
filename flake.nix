{
  description = "Python dev environment for repo-manager";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }:
  let
    system = "x86_64-linux"; # adjust if needed
    pkgs = import nixpkgs { inherit system; };
  in {
    devShells.${system}.default = pkgs.mkShell {
      buildInputs = [
        (pkgs.python3.withPackages (ps: with ps; [
          requests
        ]))
      ];

      shellHook = ''
        echo "Python environment ready (requests installed)"
        python --version
      '';
    };
  };
}
