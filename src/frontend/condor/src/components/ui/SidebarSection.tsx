import {
  Disclosure,
  DisclosureButton,
  DisclosurePanel,
  Transition,
} from "@headlessui/react";
import { ChevronDown } from "lucide-react";
import type { SidebarSectionProps } from "../../types/Sidebar";

export default function SidebarSection({
  title,
  icon: Icon,
  children,
  defaultOpen = true,
}: SidebarSectionProps) {
  return (
    <Disclosure
      defaultOpen={defaultOpen}
      as="div"
      className="border-b border-zinc-800/50 pb-4"
    >
      {({ open }) => (
        <>
          <DisclosureButton className="flex w-full items-center justify-between py-2 text-left focus:outline-none group">
            <div className="flex items-center gap-3">
              <Icon
                size={16}
                className={`${open ? "text-sky-400" : "text-zinc-500"} transition-colors`}
              />
              <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-zinc-400 group-hover:text-zinc-200">
                {title}
              </span>
            </div>
            <ChevronDown
              size={14}
              className={`text-zinc-300 transition-transform duration-200 ${open ? "rotate-180" : ""}`}
            />
          </DisclosureButton>

          <Transition
            enter="transition duration-100 ease-out"
            enterFrom="transform scale-95 opacity-0"
            enterTo="transform scale-100 opacity-100"
            leave="transition duration-75 ease-out"
            leaveFrom="transform scale-100 opacity-100"
            leaveTo="transform scale-95 opacity-0"
          >
            <DisclosurePanel className="mt-4">{children}</DisclosurePanel>
          </Transition>
        </>
      )}
    </Disclosure>
  );
}
