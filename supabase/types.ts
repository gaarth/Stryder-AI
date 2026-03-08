export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  // Allows to automatically instantiate createClient with right options
  // instead of createClient<Database, { PostgrestVersion: 'XX' }>(URL, KEY)
  __InternalSupabase: {
    PostgrestVersion: "14.4"
  }
  public: {
    Tables: {
      agent_learning_logs: {
        Row: {
          agent_name: string
          confidence: number | null
          created_at: string | null
          id: number
          log_message: string
          sim_time: string | null
        }
        Insert: {
          agent_name: string
          confidence?: number | null
          created_at?: string | null
          id?: number
          log_message: string
          sim_time?: string | null
        }
        Update: {
          agent_name?: string
          confidence?: number | null
          created_at?: string | null
          id?: number
          log_message?: string
          sim_time?: string | null
        }
        Relationships: []
      }
      agent_memory: {
        Row: {
          agent_name: string | null
          content: Json | null
          created_at: string | null
          id: number
          memory_type: string
        }
        Insert: {
          agent_name?: string | null
          content?: Json | null
          created_at?: string | null
          id?: number
          memory_type: string
        }
        Update: {
          agent_name?: string | null
          content?: Json | null
          created_at?: string | null
          id?: number
          memory_type?: string
        }
        Relationships: []
      }
      cascade_alerts: {
        Row: {
          alert_type: string
          confidence: number | null
          created_at: string | null
          id: number
          impact_count: number | null
          location: string
          location_id: string | null
          potential_impact: number | null
          resolved: boolean | null
          suggested_action: string | null
        }
        Insert: {
          alert_type: string
          confidence?: number | null
          created_at?: string | null
          id?: number
          impact_count?: number | null
          location: string
          location_id?: string | null
          potential_impact?: number | null
          resolved?: boolean | null
          suggested_action?: string | null
        }
        Update: {
          alert_type?: string
          confidence?: number | null
          created_at?: string | null
          id?: number
          impact_count?: number | null
          location?: string
          location_id?: string | null
          potential_impact?: number | null
          resolved?: boolean | null
          suggested_action?: string | null
        }
        Relationships: []
      }
      ports: {
        Row: {
          capacity: number | null
          city: string
          congestion_level: string | null
          congestion_pct: number | null
          created_at: string | null
          id: string
          incoming_count: number | null
          latitude: number
          longitude: number
          name: string
          throughput: number | null
        }
        Insert: {
          capacity?: number | null
          city: string
          congestion_level?: string | null
          congestion_pct?: number | null
          created_at?: string | null
          id: string
          incoming_count?: number | null
          latitude: number
          longitude: number
          name: string
          throughput?: number | null
        }
        Update: {
          capacity?: number | null
          city?: string
          congestion_level?: string | null
          congestion_pct?: number | null
          created_at?: string | null
          id?: string
          incoming_count?: number | null
          latitude?: number
          longitude?: number
          name?: string
          throughput?: number | null
        }
        Relationships: []
      }
      routes: {
        Row: {
          created_at: string | null
          destination_id: string
          distance_km: number | null
          id: number
          origin_id: string
          waypoints: Json | null
        }
        Insert: {
          created_at?: string | null
          destination_id: string
          distance_km?: number | null
          id?: number
          origin_id: string
          waypoints?: Json | null
        }
        Update: {
          created_at?: string | null
          destination_id?: string
          distance_km?: number | null
          id?: number
          origin_id?: string
          waypoints?: Json | null
        }
        Relationships: []
      }
      scenario_history: {
        Row: {
          affected_count: number | null
          created_at: string | null
          description: string | null
          disruption_id: number | null
          id: number
          location: string
          scenario_type: string
        }
        Insert: {
          affected_count?: number | null
          created_at?: string | null
          description?: string | null
          disruption_id?: number | null
          id?: number
          location: string
          scenario_type: string
        }
        Update: {
          affected_count?: number | null
          created_at?: string | null
          description?: string | null
          disruption_id?: number | null
          id?: number
          location?: string
          scenario_type?: string
        }
        Relationships: [
          {
            foreignKeyName: "scenario_history_disruption_id_fkey"
            columns: ["disruption_id"]
            isOneToOne: false
            referencedRelation: "simulation_events"
            referencedColumns: ["id"]
          },
        ]
      }
      shipments: {
        Row: {
          base_cost: number | null
          cargo: string | null
          carrier: string
          created_at: string | null
          current_cost: number | null
          delay_penalty_per_hour: number | null
          destination_city: string
          destination_id: string | null
          disrupted: boolean | null
          disruption_id: number | null
          eta_hours: number | null
          id: number
          latitude: number | null
          longitude: number | null
          origin_city: string
          origin_id: string | null
          priority: string | null
          progress: number | null
          risk: string | null
          status: string | null
          updated_at: string | null
        }
        Insert: {
          base_cost?: number | null
          cargo?: string | null
          carrier: string
          created_at?: string | null
          current_cost?: number | null
          delay_penalty_per_hour?: number | null
          destination_city: string
          destination_id?: string | null
          disrupted?: boolean | null
          disruption_id?: number | null
          eta_hours?: number | null
          id: number
          latitude?: number | null
          longitude?: number | null
          origin_city: string
          origin_id?: string | null
          priority?: string | null
          progress?: number | null
          risk?: string | null
          status?: string | null
          updated_at?: string | null
        }
        Update: {
          base_cost?: number | null
          cargo?: string | null
          carrier?: string
          created_at?: string | null
          current_cost?: number | null
          delay_penalty_per_hour?: number | null
          destination_city?: string
          destination_id?: string | null
          disrupted?: boolean | null
          disruption_id?: number | null
          eta_hours?: number | null
          id?: number
          latitude?: number | null
          longitude?: number | null
          origin_city?: string
          origin_id?: string | null
          priority?: string | null
          progress?: number | null
          risk?: string | null
          status?: string | null
          updated_at?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "shipments_origin_id_fkey"
            columns: ["origin_id"]
            isOneToOne: false
            referencedRelation: "ports"
            referencedColumns: ["id"]
          },
        ]
      }
      simulation_events: {
        Row: {
          affected_count: number | null
          affected_shipments: number[] | null
          created_at: string | null
          eta_impact_h: number | null
          event_name: string | null
          event_type: string
          id: number
          location: string
          location_id: string | null
          resolved: boolean | null
          scenario_type: string | null
          severity: string | null
          timestamp: string | null
        }
        Insert: {
          affected_count?: number | null
          affected_shipments?: number[] | null
          created_at?: string | null
          eta_impact_h?: number | null
          event_name?: string | null
          event_type: string
          id?: number
          location: string
          location_id?: string | null
          resolved?: boolean | null
          scenario_type?: string | null
          severity?: string | null
          timestamp?: string | null
        }
        Update: {
          affected_count?: number | null
          affected_shipments?: number[] | null
          created_at?: string | null
          eta_impact_h?: number | null
          event_name?: string | null
          event_type?: string
          id?: number
          location?: string
          location_id?: string | null
          resolved?: boolean | null
          scenario_type?: string | null
          severity?: string | null
          timestamp?: string | null
        }
        Relationships: []
      }
      system_metrics: {
        Row: {
          id: number
          metric_name: string
          metric_text: string | null
          metric_type: string | null
          metric_value: number | null
          sim_time: string | null
          timestamp: string | null
        }
        Insert: {
          id?: number
          metric_name: string
          metric_text?: string | null
          metric_type?: string | null
          metric_value?: number | null
          sim_time?: string | null
          timestamp?: string | null
        }
        Update: {
          id?: number
          metric_name?: string
          metric_text?: string | null
          metric_type?: string | null
          metric_value?: number | null
          sim_time?: string | null
          timestamp?: string | null
        }
        Relationships: []
      }
      warehouses: {
        Row: {
          capacity: number | null
          city: string
          created_at: string | null
          id: string
          incoming_count: number | null
          latitude: number
          longitude: number
          name: string
          utilization_pct: number | null
        }
        Insert: {
          capacity?: number | null
          city: string
          created_at?: string | null
          id: string
          incoming_count?: number | null
          latitude: number
          longitude: number
          name: string
          utilization_pct?: number | null
        }
        Update: {
          capacity?: number | null
          city?: string
          created_at?: string | null
          id?: string
          incoming_count?: number | null
          latitude?: number
          longitude?: number
          name?: string
          utilization_pct?: number | null
        }
        Relationships: []
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      [_ in never]: never
    }
    Enums: {
      [_ in never]: never
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}

type DatabaseWithoutInternals = Omit<Database, "__InternalSupabase">

type DefaultSchema = DatabaseWithoutInternals[Extract<keyof Database, "public">]

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] &
        DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] &
        DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R
      }
      ? R
      : never
    : never

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I
      }
      ? I
      : never
    : never

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U
      }
      ? U
      : never
    : never

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    | keyof DefaultSchema["Enums"]
    | { schema: keyof DatabaseWithoutInternals },
  EnumName extends DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never = never,
> = DefaultSchemaEnumNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
    ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
    : never

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema["CompositeTypes"]
    | { schema: keyof DatabaseWithoutInternals },
  CompositeTypeName extends PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never = never,
> = PublicCompositeTypeNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
    ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never

export const Constants = {
  public: {
    Enums: {},
  },
} as const
