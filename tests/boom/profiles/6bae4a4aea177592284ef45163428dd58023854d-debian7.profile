BOOM_OS_ID="6bae4a4aea177592284ef45163428dd58023854d"
BOOM_OS_NAME="Debian GNU/Linux"
BOOM_OS_SHORT_NAME="debian"
BOOM_OS_VERSION="7 (wheezy)"
BOOM_OS_VERSION_ID="7"
BOOM_OS_UNAME_PATTERN="deb7"
BOOM_OS_KERNEL_PATTERN="/kernel-%{version}"
BOOM_OS_INITRAMFS_PATTERN="/initramfs-%{version}.img"
BOOM_OS_ROOT_OPTS_LVM2="rd.lvm.lv=%{lvm_root_lv}"
BOOM_OS_ROOT_OPTS_BTRFS="rootflags=%{btrfs_subvolume}"
BOOM_OS_OPTIONS="root=%{root_device} ro %{root_opts}"
