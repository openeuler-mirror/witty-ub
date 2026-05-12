#include "urma_1148_urma_free_net_addr_list_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1148UrmaFreeNetAddrListFunctionFailure> g_urma("urma_1148");

bool Urma1148UrmaFreeNetAddrListFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1149"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1148UrmaFreeNetAddrListFunctionFailure::GetName() const
{
    return "urma_free_net_addr_list 函数故障";
}

std::string Urma1148UrmaFreeNetAddrListFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1148UrmaFreeNetAddrListFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1148UrmaFreeNetAddrListFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1148UrmaFreeNetAddrListFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1148UrmaFreeNetAddrListFunctionFailure::GetId() const
{
    return "urma_1148";
}
} // namespace diag
