import React from 'react';

export const Spinner: React.FC = () => {
  return (
    // Frosted glass map overlay
    <div className="absolute inset-0 bg-zinc-600/70 backdrop-blur-sm z-[1500] flex flex-col justify-center items-center select-none">
      <div className="flex flex-col items-center gap-5">

        {/* Animated Icon Frame */}
        <div className="relative w-16 h-16 flex justify-center items-center">

          {/* LAYER 1: The Pulse Wave (Route Orange) */}
          <div className="absolute inset-0 bg-[#ff7800]/10 border border-[#ff7800]/40 rounded-full animate-radar-wave" />

          {/* LAYER 2: Core Base Ring */}

          {/* LAYER 3: The Compass Icon Component */}
            <div className="relative z-10 text-zinc-700 animate-compass-turn">
                <svg xmlns="http://www.w3.org/2000/svg" width="72" height="72" viewBox="0 0 24 24" fill="none"
                     stroke="currentColor" strokeWidth="2.25" strokeLinecap="round" strokeLinejoin="round"
                     className="lucide compass lucide-compass">
                    <circle fill={"white"} cx="12" cy="12" r="10" className="text-map-gold bg-white"/>

                    <path
                        d="M 16.24 7.76 L 14.436 13.171 A 2 2 0 0 1 13.804 13.804 L 10.196 10.196 A 2 2 0 0 1 10.829 9.564 Z"
                        className="text-red-500 fill-red-500"
                    />

                    <path
                        d="M 7.76 16.24 L 9.564 10.829 A 2 2 0 0 1 10.196 10.196 L 13.804 13.804 A 2 2 0 0 1 13.171 14.436 Z"
                        className="text-gray-700 fill-gray-700"
                    />
                </svg>
            </div>


        </div>

          {/* Contextual Progress Text */}
          <div className="flex flex-col items-center text-center font-sans gap-0.5">
              <span className="text-sm font-bold text-white">Calcul de l'itinéraire...</span>
              <span className="text-xs font-medium text-white animate-text-pulse">
            Ajustement des contraintes terrain
          </span>
          </div>

      </div>
    </div>
  );
};