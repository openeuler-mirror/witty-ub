#include "urma_failure_098.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure098> g_urma("urma_098");

bool UrmaFailure098::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'handle_recv_cr_with_store' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to find local jetty, idx:' | grep -F ', id:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure098::GetName() const
{
    return "未找到可用于获取Jetty的有效对象或路由";
}

std::string UrmaFailure098::GetRootCauseDesc() const
{
    return "函数在获取Jetty过程中需要查找已建立的资源、端口或路由映射，但当前表项缺失或状态不可用，导致后续操作无法定位"
           "目标。";
}

RootCause UrmaFailure098::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure098::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure098::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：handle_recv_cr_with_store，Failed to find local jetty, idx:，, id:";
}

std::string UrmaFailure098::GetId() const
{
    return "urma_098";
}

} // namespace diag
