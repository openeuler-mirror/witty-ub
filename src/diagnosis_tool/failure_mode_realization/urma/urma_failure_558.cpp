#include "urma_failure_558.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure558> g_urma("urma_558");

bool UrmaFailure558::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_get_device_by_name' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'device list name: does not match dev_name')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure558::GetName() const
{
    return "urma_get_device_by_name 校验 设备 业务条件不满足导致获取流程拒绝继续执行";
}

std::string UrmaFailure558::GetRootCauseDesc() const
{
    return "urma_get_device_by_name 在执行获取时发现 设备 "
           "的传输模式、绑定关系、路由选择、数量限制或设备属性与当前操作要求不一致，因此直接返回错误，避免建立错误的资"
           "源关系或下发不被支持的请求。";
}

RootCause UrmaFailure558::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure558::GetFixSuggDesc() const
{
    return "执行 `lsmod | grep udma` 检查驱动是否加载，执行 `urma_admin show -a` 查看 UB 设备是否存在，部署完成后重试";
}

std::string UrmaFailure558::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：device list name: does not match dev_name";
}

std::string UrmaFailure558::GetId() const
{
    return "urma_558";
}

} // namespace diag
