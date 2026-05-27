#include "urma_failure_635.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure635> g_urma("urma_635");

bool UrmaFailure635::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_delete_jfc' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure635::GetName() const
{
    return "URMA context无效导致删除JFC失败";
}

std::string UrmaFailure635::GetRootCauseDesc() const
{
    return "函数用于删除JFC，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure635::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure635::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure635::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_delete_jfc，Invalid parameter。";
}

std::string UrmaFailure635::GetId() const
{
    return "urma_635";
}

} // namespace diag
