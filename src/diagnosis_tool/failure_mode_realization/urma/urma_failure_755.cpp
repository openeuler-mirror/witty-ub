#include "urma_failure_755.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure755> g_urma("urma_755");

bool UrmaFailure755::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_deactive_jfc' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure755::GetName() const
{
    return "URMA context无效导致去激活JFC失败";
}

std::string UrmaFailure755::GetRootCauseDesc() const
{
    return "函数用于去激活JFC，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure755::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure755::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure755::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_deactive_jfc，Invalid parameter。";
}

std::string UrmaFailure755::GetId() const
{
    return "urma_755";
}

} // namespace diag
