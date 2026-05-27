#include "urma_failure_362.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure362> g_urma("urma_362");

bool UrmaFailure362::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_alloc_token_id_ex' "
                                    "\"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure362::GetName() const
{
    return "URMA context无效导致分配Token失败";
}

std::string UrmaFailure362::GetRootCauseDesc() const
{
    return "函数用于分配Token，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure362::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure362::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure362::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_alloc_token_id_ex，Invalid parameter。";
}

std::string UrmaFailure362::GetId() const
{
    return "urma_362";
}

} // namespace diag
