#include "urma_failure_486.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure486> g_urma("urma_486");

bool UrmaFailure486::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_read' \"$URMA_LOG_PATH\" 2>/dev/null "
                                    "| grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure486::GetName() const
{
    return "JFS对象、WR对象无效导致读取JFS失败";
}

std::string UrmaFailure486::GetRootCauseDesc() const
{
    return "函数用于读取JFS，调用方传入的JFS对象、WR对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure486::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure486::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure486::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_read，Invalid parameter.";
}

std::string UrmaFailure486::GetId() const
{
    return "urma_486";
}

} // namespace diag
