#include "urma_failure_652.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure652> g_urma("urma_652");

bool UrmaFailure652::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_delete_jfc' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure652::GetName() const
{
    return "URMA context、provider操作表无效导致删除JFC失败";
}

std::string UrmaFailure652::GetRootCauseDesc() const
{
    return "函数用于删除JFC，调用方传入的URMA context、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure652::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure652::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure652::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_delete_jfc，Invalid parameter.。";
}

std::string UrmaFailure652::GetId() const
{
    return "urma_652";
}

} // namespace diag
