#include "urma_failure_422.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure422> g_urma("urma_422");

bool UrmaFailure422::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'handle_send_cr_with_store' \"$URMA_LOG_PATH\" 2>/dev/null | grep -F "
        "'Failed to find valid port for retransmission.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure422::GetName() const
{
    return "未找到可用于修改端口的有效对象或路由";
}

std::string UrmaFailure422::GetRootCauseDesc() const
{
    return "函数在修改端口过程中需要查找已建立的资源、端口或路由映射，但当前表项缺失或状态不可用，导致后续操作无法定位"
           "目标。";
}

RootCause UrmaFailure422::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure422::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure422::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：handle_send_cr_with_store，Failed to find valid port for "
           "retransmission.。";
}

std::string UrmaFailure422::GetId() const
{
    return "urma_422";
}

} // namespace diag
