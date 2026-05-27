#include "urma_failure_096.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure096> g_urma("urma_096");

bool UrmaFailure096::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'handle_fake_cr_with_store' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Skip fake cr because vjetty is not found, idx:' | grep -F ', local_id:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure096::GetName() const
{
    return "未找到可用于获取虚拟 Jetty的有效对象或路由";
}

std::string UrmaFailure096::GetRootCauseDesc() const
{
    return "函数在获取虚拟 "
           "Jetty过程中需要查找已建立的资源、端口或路由映射，但当前表项缺失或状态不可用，导致后续操作无法定位目标。";
}

RootCause UrmaFailure096::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure096::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure096::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：handle_fake_cr_with_store，Skip fake cr because vjetty is not found, idx:，, "
           "local_id:";
}

std::string UrmaFailure096::GetId() const
{
    return "urma_096";
}

} // namespace diag
