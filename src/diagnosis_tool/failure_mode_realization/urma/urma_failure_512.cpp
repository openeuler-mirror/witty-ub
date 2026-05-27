#include "urma_failure_512.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure512> g_urma("urma_512");

bool UrmaFailure512::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_create_pseg' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid segment address for bondp seg'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure512::GetName() const
{
    return "Segment对象无效导致创建Segment失败";
}

std::string UrmaFailure512::GetRootCauseDesc() const
{
    return "函数用于创建Segment，调用方传入的Segment对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure512::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure512::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure512::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_create_pseg，Invalid segment address for bondp seg。";
}

std::string UrmaFailure512::GetId() const
{
    return "urma_512";
}

} // namespace diag
