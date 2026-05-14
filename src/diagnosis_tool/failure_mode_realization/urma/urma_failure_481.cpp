#include "urma_failure_481.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure481> g_urma("urma_481");

bool UrmaFailure481::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_get_eid_list' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'max eid cnt is err')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure481::GetName() const
{
    return "urma_get_eid_list 读取或解析 sysfs 设备/EID/端口信息失败导致设备信息不可用";
}

std::string UrmaFailure481::GetRootCauseDesc() const
{
    return "urma_get_eid_list 依赖 sysfs 中的设备、EID、端口、能力或 cdev 路径信息枚举 URMA "
           "设备并构建设备属性，但文件打开、读取、格式化路径或内容解析失败，导致设备、端口或 EID "
           "信息无法被用户态正确使用。";
}

RootCause UrmaFailure481::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure481::GetFixSuggDesc() const
{
    return "执行 `lsmod | grep udma` 检查驱动是否加载，执行 `urma_admin show -a` 查看 UB 设备是否存在，部署完成后重试";
}

std::string UrmaFailure481::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：max eid cnt is err";
}

std::string UrmaFailure481::GetId() const
{
    return "urma_481";
}

} // namespace diag
