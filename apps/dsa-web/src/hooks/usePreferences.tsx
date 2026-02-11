import { createContext, useContext, useEffect, useState } from 'react';
import type React from 'react';
import apiClient from '../api';

interface Preferences {
  greenUpRedDown: boolean;
}

const DEFAULT_PREFERENCES: Preferences = {
  greenUpRedDown: true,
};

const PreferencesContext = createContext<Preferences>(DEFAULT_PREFERENCES);

export const PreferencesProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [prefs, setPrefs] = useState<Preferences>(DEFAULT_PREFERENCES);

  useEffect(() => {
    apiClient
      .get<{ green_up_red_down: boolean }>('/api/v1/system/preferences')
      .then((res) => {
        setPrefs({ greenUpRedDown: res.data.green_up_red_down });
      })
      .catch(() => {
        // Keep defaults on failure
      });
  }, []);

  return <PreferencesContext.Provider value={prefs}>{children}</PreferencesContext.Provider>;
};

export const usePreferences = (): Preferences => useContext(PreferencesContext);
