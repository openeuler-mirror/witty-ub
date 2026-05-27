#include "urma_failure_776.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure776> g_urma("urma_776");

bool UrmaFailure776::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_set_jfc_opt' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'invalid opt id or opt len'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure776::GetName() const
{
    return "provider操作表无效导致设置JFC失败";
}

std::string UrmaFailure776::GetRootCauseDesc() const
{
    return "函数用于设置JFC，调用方传入的provider操作表不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure776::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure776::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure776::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_set_jfc_opt，invalid opt id or opt len。";
}

std::string UrmaFailure776::GetId() const
{
    return "urma_776";
}

} // namespace diag
