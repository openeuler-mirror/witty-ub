#include "urma_failure_769.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure769> g_urma("urma_769");

bool UrmaFailure769::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_check_trans_mode_valid' "
                                    "\"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure769::GetName() const
{
    return "URMA context无效导致创建JFC失败";
}

std::string UrmaFailure769::GetRootCauseDesc() const
{
    return "函数用于创建JFC，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure769::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure769::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure769::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_check_trans_mode_valid，Invalid parameter.。";
}

std::string UrmaFailure769::GetId() const
{
    return "urma_769";
}

} // namespace diag
