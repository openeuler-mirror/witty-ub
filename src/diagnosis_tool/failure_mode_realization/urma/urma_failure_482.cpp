#include "urma_failure_482.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure482> g_urma("urma_482");

bool UrmaFailure482::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_parse_port_attr' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'snprintf failed, path:' | grep -F ', port_num:' | grep -F 'hu.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure482::GetName() const
{
    return "解析端口过程中依赖步骤失败";
}

std::string UrmaFailure482::GetRootCauseDesc() const
{
    return "函数用于解析端口，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操"
           "作失败。";
}

RootCause UrmaFailure482::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure482::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure482::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_parse_port_attr，snprintf failed, path:，, port_num:，hu.";
}

std::string UrmaFailure482::GetId() const
{
    return "urma_482";
}

} // namespace diag
