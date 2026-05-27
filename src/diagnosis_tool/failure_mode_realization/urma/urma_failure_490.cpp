#include "urma_failure_490.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure490> g_urma("urma_490");

bool UrmaFailure490::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_read' \"$URMA_LOG_PATH\" 2>/dev/null "
                                    "| grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure490::GetName() const
{
    return "JFS对象、WR对象无效导致读取JFS失败";
}

std::string UrmaFailure490::GetRootCauseDesc() const
{
    return "函数用于读取JFS，调用方传入的JFS对象、WR对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure490::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure490::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure490::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_read，Invalid parameter.。";
}

std::string UrmaFailure490::GetId() const
{
    return "urma_490";
}

} // namespace diag
