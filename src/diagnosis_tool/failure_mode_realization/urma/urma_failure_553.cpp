#include "urma_failure_553.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure553> g_urma("urma_553");

bool UrmaFailure553::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_get_device_list' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Invalid parameter')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure553::GetName() const
{
    return "urma_get_device_list 校验 设备 无效导致获取流程拒绝继续执行";
}

std::string UrmaFailure553::GetRootCauseDesc() const
{
    return "urma_get_device_list 在执行获取前发现调用方传入的 设备 不满足当前操作要求，通常是对象为空、状态不匹配或与 "
           "provider 能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure553::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure553::GetFixSuggDesc() const
{
    return "执行 `lsmod | grep udma` 检查驱动是否加载，执行 `urma_admin show -a` 查看 UB 设备是否存在，部署完成后重试";
}

std::string UrmaFailure553::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid parameter";
}

std::string UrmaFailure553::GetId() const
{
    return "urma_553";
}

} // namespace diag
