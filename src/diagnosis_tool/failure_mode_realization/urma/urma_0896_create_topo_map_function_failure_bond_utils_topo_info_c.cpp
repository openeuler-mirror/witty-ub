#include "urma_0896_create_topo_map_function_failure_bond_utils_topo_info_c.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0896CreateTopoMapFunctionFailureBondUtilsTopoInfoC> g_urma("urma_0896");

bool Urma0896CreateTopoMapFunctionFailureBondUtilsTopoInfoC::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0897", "urma_0898", "urma_0899"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0896CreateTopoMapFunctionFailureBondUtilsTopoInfoC::GetName() const
{
    return "create_topo_map 函数故障（bond/utils/topo_info.c）";
}

std::string Urma0896CreateTopoMapFunctionFailureBondUtilsTopoInfoC::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0896CreateTopoMapFunctionFailureBondUtilsTopoInfoC::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0896CreateTopoMapFunctionFailureBondUtilsTopoInfoC::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0896CreateTopoMapFunctionFailureBondUtilsTopoInfoC::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0896CreateTopoMapFunctionFailureBondUtilsTopoInfoC::GetId() const
{
    return "urma_0896";
}
} // namespace diag
