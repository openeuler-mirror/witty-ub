#include "urma_failure_106.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure106> g_urma("urma_106");

bool UrmaFailure106::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'import_check_tseg_by_import_result' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'No valid imported route for health check seg'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure106::GetName() const
{
    return "未找到可用于导入路由的有效对象或路由";
}

std::string UrmaFailure106::GetRootCauseDesc() const
{
    return "函数在导入路由过程中需要查找已建立的资源、端口或路由映射，但当前表项缺失或状态不可用，导致后续操作无法定位"
           "目标。";
}

RootCause UrmaFailure106::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure106::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure106::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：import_check_tseg_by_import_result，No valid imported route for health "
           "check seg。";
}

std::string UrmaFailure106::GetId() const
{
    return "urma_106";
}

} // namespace diag
