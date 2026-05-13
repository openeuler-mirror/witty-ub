#include "urma_0999_bondp_v_segment_register_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0999BondpVSegmentRegisterFunctionFailure> g_urma("urma_0999");

bool Urma0999BondpVSegmentRegisterFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1000"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0999BondpVSegmentRegisterFunctionFailure::GetName() const
{
    return "bondp_v_segment_register 函数故障";
}

std::string Urma0999BondpVSegmentRegisterFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0999BondpVSegmentRegisterFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0999BondpVSegmentRegisterFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0999BondpVSegmentRegisterFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0999BondpVSegmentRegisterFunctionFailure::GetId() const
{
    return "urma_0999";
}
} // namespace diag
