"use client";

import { useState } from "react";
import {
  Label,
  Listbox,
  ListboxButton,
  ListboxOption,
  ListboxOptions,
} from "@headlessui/react";
import { ChevronUpDownIcon } from "@heroicons/react/16/solid";
import { CheckIcon } from "@heroicons/react/20/solid";
import type { MenuProps } from "../../types/Select.ts";

export default function SelectList<K extends string>({
  labels,
  onSelect,
  labelTitle,
}: MenuProps<K>) {
  const options = Object.entries(labels) as [K, string][];
  const [selectedKey, setSelectedKey] = useState<K>(options[0]?.[0]);

  const handleChange = (key: K) => {
    setSelectedKey(key);
    onSelect?.(key);
  };

  return (
    <Listbox value={selectedKey} onChange={handleChange}>
      {labelTitle && (
        <Label className="text-[11px] text-zinc-300  tracking-wider mb-1.5 block">
          {labelTitle}
        </Label>
      )}

      <div className="relative">
        {" "}
        {/* Removed mt-2 to tighten spacing */}
        <ListboxButton className="grid w-full cursor-default grid-cols-1 rounded-lg bg-zinc-800 border border-zinc-700 py-1.5 pl-2 pr-2 text-left text-[11px] text-zinc-300 outline-none focus:border-sky-500/50 transition-colors">
          <span className="col-start-1 row-start-1 truncate pr-6">
            {labels[selectedKey]}
          </span>
          <ChevronUpDownIcon className="col-start-1 row-start-1 size-4 self-center justify-self-end text-zinc-500" />
        </ListboxButton>
        <ListboxOptions
          transition
          anchor="bottom start"
          className="z-[10000] mt-1 max-h-60 w-[var(--button-width)] overflow-auto rounded-md bg-zinc-800 py-1 text-[11px] shadow-2xl ring-1 ring-zinc-700 focus:outline-none"
        >
          {options.map(([key, value]) => (
            <ListboxOption
              key={key}
              value={key}
              className="group relative cursor-default py-1.5 pl-3 pr-8 text-zinc-300 select-none data-focus:bg-sky-600 data-focus:text-white"
            >
              <span className="block truncate font-normal group-data-selected:font-semibold group-data-selected:text-sky-400 group-data-focus:text-white">
                {value}
              </span>

              <span className="absolute inset-y-0 right-0 flex items-center pr-2 text-sky-500 group-not-data-selected:hidden group-data-focus:text-white">
                <CheckIcon aria-hidden="true" className="size-4" />
              </span>
            </ListboxOption>
          ))}
        </ListboxOptions>
      </div>
    </Listbox>
  );
}
