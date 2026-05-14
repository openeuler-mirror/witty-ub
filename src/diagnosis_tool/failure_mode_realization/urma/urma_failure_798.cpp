#include "urma_failure_798.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure798> g_urma("urma_798");

bool UrmaFailure798::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_delete_jetty_batch' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Failed to delete as jetty has remote jetty, try unbind, index')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure798::GetName() const
{
    return "urma_delete_jetty_batch 读取或解析 sysfs 设备/EID/端口信息失败导致设备信息不可用";
}

std::string UrmaFailure798::GetRootCauseDesc() const
{
    return "urma_delete_jetty_batch 依赖 sysfs 中的设备、EID、端口、能力或 cdev 路径信息枚举 URMA "
           "设备并构建设备属性，但文件打开、读取、格式化路径或内容解析失败，导致设备、端口或 EID "
           "信息无法被用户态正确使用。";
}

RootCause UrmaFailure798::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure798::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure798::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to delete as jetty has remote jetty, try unbind, index";
}

std::string UrmaFailure798::GetId() const
{
    return "urma_798";
}

} // namespace diag
