#include "urma_failure_133.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure133> g_urma("urma_133");

bool UrmaFailure133::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'urma_bind_jetty' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Not allowed to bind local jetty: of mode: with remote jetty: of mode'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure133::GetName() const
{
    return "urma_bind_jetty 读取或解析 sysfs 设备/EID/端口信息失败导致设备信息不可用";
}

std::string UrmaFailure133::GetRootCauseDesc() const
{
    return "urma_bind_jetty 依赖 sysfs 中的设备、EID、端口、能力或 cdev 路径信息枚举 URMA "
           "设备并构建设备属性，但文件打开、读取、格式化路径或内容解析失败，导致设备、端口或 EID "
           "信息无法被用户态正确使用。";
}

RootCause UrmaFailure133::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure133::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure133::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Not allowed to bind local jetty: of mode: with remote jetty: of mode";
}

std::string UrmaFailure133::GetId() const
{
    return "urma_133";
}

} // namespace diag
