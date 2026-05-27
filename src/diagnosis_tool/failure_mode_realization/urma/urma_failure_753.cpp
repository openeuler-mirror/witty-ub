#include "urma_failure_753.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure753> g_urma("urma_753");

bool UrmaFailure753::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_deactive_jfr' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure753::GetName() const
{
    return "URMA context、JFR对象无效导致去激活JFR失败";
}

std::string UrmaFailure753::GetRootCauseDesc() const
{
    return "函数用于去激活JFR，调用方传入的URMA context、JFR对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure753::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure753::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure753::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_cmd_deactive_jfr，Invalid parameter";
}

std::string UrmaFailure753::GetId() const
{
    return "urma_753";
}

} // namespace diag
