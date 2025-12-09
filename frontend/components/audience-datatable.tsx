"use client";

import { useState, useMemo } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Search, ChevronUp, ChevronDown, Download } from "lucide-react";
import type { AudienceMember } from "@/types/audience";

interface AudienceDatatableProps {
  data: AudienceMember[];
  audienceName: string;
  onBack: () => void;
}

export function AudienceDatatable({
  data,
  audienceName,
  onBack,
}: AudienceDatatableProps) {
  const [searchTerm, setSearchTerm] = useState("");
  const [sortColumn, setSortColumn] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("asc");
  const [vehicleTypeFilter, setVehicleTypeFilter] = useState<string>("all");
  const [cityFilter, setCityFilter] = useState<string>("all");
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10;

  // Extract unique values for filters
  const vehicleTypes = useMemo(
    () =>
      Array.from(
        new Set(
          data
            .map((item) => item.vehicle_model || item.vehicleType)
            .filter(Boolean)
        )
      ).sort(),
    [data]
  );
  const cities = useMemo(
    () =>
      Array.from(new Set(data.map((item) => item.city).filter(Boolean))).sort(),
    [data]
  );

  const filteredAndSortedData = useMemo(() => {
    let filtered = data.filter((item) => {
      const personName = item.person_name || item.name || "";
      const phoneNumber = item.phone_number || item.phoneNumber || "";
      const email = item.email || "";

      const city = item.city || "";

      const matchesSearch =
        personName.toLowerCase().includes(searchTerm.toLowerCase()) ||
        phoneNumber.includes(searchTerm) ||
        city.toLowerCase().includes(searchTerm.toLowerCase());

      const vehicleModel = item.vehicle_model || item.vehicleType || "";
      const matchesVehicleType =
        vehicleTypeFilter === "all" || vehicleModel === vehicleTypeFilter;
      const matchesCity = cityFilter === "all" || city === cityFilter;

      return matchesSearch && matchesVehicleType && matchesCity;
    });

    if (sortColumn) {
      filtered = filtered.sort((a, b) => {
        let aValue: any;
        let bValue: any;

        // Handle field name mapping
        if (sortColumn === "person_name") {
          aValue = a.person_name || a.name || "";
          bValue = b.person_name || b.name || "";
        } else if (sortColumn === "vehicle_model") {
          aValue = a.vehicle_model || a.vehicleType || "";
          bValue = b.vehicle_model || b.vehicleType || "";
        } else if (sortColumn === "city") {
          aValue = a.city || "";
          bValue = b.city || "";
        } else {
          aValue = (a as any)[sortColumn] || "";
          bValue = (b as any)[sortColumn] || "";
        }

        if (typeof aValue === "string" && typeof bValue === "string") {
          return sortDirection === "asc"
            ? aValue.localeCompare(bValue)
            : bValue.localeCompare(aValue);
        }
        if (typeof aValue === "number" && typeof bValue === "number") {
          return sortDirection === "asc" ? aValue - bValue : bValue - aValue;
        }
        return 0;
      });
    }

    return filtered;
  }, [
    data,
    searchTerm,
    sortColumn,
    sortDirection,
    vehicleTypeFilter,
    cityFilter,
  ]);

  const paginatedData = useMemo(() => {
    const startIndex = (currentPage - 1) * itemsPerPage;
    return filteredAndSortedData.slice(startIndex, startIndex + itemsPerPage);
  }, [filteredAndSortedData, currentPage]);

  const totalPages = Math.ceil(filteredAndSortedData.length / itemsPerPage);

  const handleSort = (column: string) => {
    if (sortColumn === column) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc");
    } else {
      setSortColumn(column);
      setSortDirection("asc");
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "Converted":
        return "bg-green-100 text-green-800 border-green-200";
      case "Qualified":
        return "bg-blue-100 text-blue-800 border-blue-200";
      case "Lead":
        return "bg-yellow-100 text-yellow-800 border-yellow-200";
      case "Losing":
        return "bg-orange-100 text-orange-800 border-orange-200";
      case "Lost":
        return "bg-red-100 text-red-800 border-red-200";
      default:
        return "bg-gray-100 text-gray-800 border-gray-200";
    }
  };

  const handleExport = () => {
    const csvContent =
      "data:text/csv;charset=utf-8," +
      "Person Name,Vehicle Model,Mobile No,City\n" +
      filteredAndSortedData
        .map(
          (item) =>
            `${item.person_name || item.name || ""},${
              item.vehicle_model || item.vehicleType || ""
            },${item.phone_number || item.phoneNumber || ""},${item.city || ""}`
        )
        .join("\n");

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute(
      "download",
      `${audienceName.toLowerCase().replace(/\s+/g, "-")}-members.csv`
    );
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>{audienceName} Members</CardTitle>
            <p className="text-sm text-muted-foreground mt-1">
              {filteredAndSortedData.length} member
              {filteredAndSortedData.length !== 1 ? "s" : ""} found
            </p>
          </div>
          <Button variant="outline" size="sm" onClick={handleExport}>
            <Download className="h-4 w-4 mr-2" />
            Export CSV
          </Button>
        </div>

        {/* Search and Filters */}
        <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center mt-4">
          <div className="relative flex-1 max-w-sm">
            <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search by name, phone, or city..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-8"
            />
          </div>

          <div className="flex gap-2 flex-wrap">
            {vehicleTypes.length > 0 && (
              <Select
                value={vehicleTypeFilter}
                onValueChange={setVehicleTypeFilter}
              >
                <SelectTrigger className="w-[140px]">
                  <SelectValue placeholder="All Vehicles" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Vehicles</SelectItem>
                  {vehicleTypes.map((type) => (
                    <SelectItem key={type} value={type}>
                      {type}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
            {cities.length > 0 && (
              <Select value={cityFilter} onValueChange={setCityFilter}>
                <SelectTrigger className="w-[140px]">
                  <SelectValue placeholder="All Cities" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Cities</SelectItem>
                  {cities.map((city) => (
                    <SelectItem key={city} value={city}>
                      {city}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent>
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead
                  className="cursor-pointer"
                  onClick={() => handleSort("person_name")}
                >
                  Person Name
                  {sortColumn === "person_name" &&
                    (sortDirection === "asc" ? (
                      <ChevronUp className="inline h-4 w-4 ml-1" />
                    ) : (
                      <ChevronDown className="inline h-4 w-4 ml-1" />
                    ))}
                </TableHead>
                <TableHead
                  className="cursor-pointer"
                  onClick={() => handleSort("vehicle_model")}
                >
                  Vehicle Model
                  {sortColumn === "vehicle_model" &&
                    (sortDirection === "asc" ? (
                      <ChevronUp className="inline h-4 w-4 ml-1" />
                    ) : (
                      <ChevronDown className="inline h-4 w-4 ml-1" />
                    ))}
                </TableHead>
                <TableHead>Mobile No</TableHead>
                <TableHead
                  className="cursor-pointer"
                  onClick={() => handleSort("city")}
                >
                  City
                  {sortColumn === "city" &&
                    (sortDirection === "asc" ? (
                      <ChevronUp className="inline h-4 w-4 ml-1" />
                    ) : (
                      <ChevronDown className="inline h-4 w-4 ml-1" />
                    ))}
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {paginatedData.length > 0 ? (
                paginatedData.map((member, index) => (
                  <TableRow
                    key={member.id || index}
                    className="hover:bg-muted/50"
                  >
                    <TableCell className="font-medium">
                      {member.person_name || member.name || "-"}
                    </TableCell>
                    <TableCell>
                      {member.vehicle_model || member.vehicleType || "-"}
                    </TableCell>
                    <TableCell>
                      {member.phone_number || member.phoneNumber || "-"}
                    </TableCell>
                    <TableCell>{member.city || "-"}</TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell
                    colSpan={4}
                    className="h-24 text-center text-muted-foreground"
                  >
                    No members found matching your criteria.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between space-x-2 py-4">
            <div className="text-sm text-muted-foreground">
              Showing {(currentPage - 1) * itemsPerPage + 1} to{" "}
              {Math.min(
                currentPage * itemsPerPage,
                filteredAndSortedData.length
              )}{" "}
              of {filteredAndSortedData.length} results
            </div>
            <div className="flex items-center space-x-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setCurrentPage((prev) => Math.max(prev - 1, 1))}
                disabled={currentPage === 1}
              >
                Previous
              </Button>
              <div className="flex items-center space-x-1">
                {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => {
                  let page;
                  if (totalPages <= 5) {
                    page = i + 1;
                  } else if (currentPage <= 3) {
                    page = i + 1;
                  } else if (currentPage >= totalPages - 2) {
                    page = totalPages - 4 + i;
                  } else {
                    page = currentPage - 2 + i;
                  }
                  return (
                    <Button
                      key={page}
                      variant={currentPage === page ? "default" : "outline"}
                      size="sm"
                      onClick={() => setCurrentPage(page)}
                      className="w-8 h-8 p-0"
                    >
                      {page}
                    </Button>
                  );
                })}
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() =>
                  setCurrentPage((prev) => Math.min(prev + 1, totalPages))
                }
                disabled={currentPage === totalPages}
              >
                Next
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
