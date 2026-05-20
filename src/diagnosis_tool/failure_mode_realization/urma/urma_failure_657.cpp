#include "urma_failure_657.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure657> g_urma("urma_657");

bool UrmaFailure657::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'handle_recv' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to get target jetty id'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure657::GetName() const
{
    return "handle_recv 读取或解析 sysfs 设备/EID/端口信息失败导致设备信息不可用";
}

std::string UrmaFailure657::GetRootCauseDesc() const
{
    return "handle_recv 依赖 sysfs 中的设备、EID、端口、能力或 cdev 路径信息枚举 URMA "
           "设备并构建设备属性，但文件打开、读取、格式化路径或内容解析失败，导致设备、端口或 EID "
           "信息无法被用户态正确使用。";
}

RootCause UrmaFailure657::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure657::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure657::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to get target jetty id";
}

std::string UrmaFailure657::GetId() const
{
    return "urma_657";
}

} // namespace diag
