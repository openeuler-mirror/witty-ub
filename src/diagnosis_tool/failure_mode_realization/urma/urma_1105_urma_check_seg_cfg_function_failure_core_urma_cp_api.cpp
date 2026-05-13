#include "urma_1105_urma_check_seg_cfg_function_failure_core_urma_cp_api.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1105UrmaCheckSegCfgFunctionFailureCoreUrmaCpApi> g_urma("urma_1105");

bool Urma1105UrmaCheckSegCfgFunctionFailureCoreUrmaCpApi::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1106", "urma_1107"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1105UrmaCheckSegCfgFunctionFailureCoreUrmaCpApi::GetName() const
{
    return "urma_check_seg_cfg 函数故障（core/urma_cp_api.c）";
}

std::string Urma1105UrmaCheckSegCfgFunctionFailureCoreUrmaCpApi::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1105UrmaCheckSegCfgFunctionFailureCoreUrmaCpApi::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1105UrmaCheckSegCfgFunctionFailureCoreUrmaCpApi::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1105UrmaCheckSegCfgFunctionFailureCoreUrmaCpApi::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1105UrmaCheckSegCfgFunctionFailureCoreUrmaCpApi::GetId() const
{
    return "urma_1105";
}
} // namespace diag
