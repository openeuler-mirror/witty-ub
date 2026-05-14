#include "urma_failure_256.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure256> g_urma("urma_256");

bool UrmaFailure256::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'init_general_slave_devices' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Invalid slave device number of device')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure256::GetName() const
{
    return "init_general_slave_devices 校验 设备 无效导致初始化流程拒绝继续执行";
}

std::string UrmaFailure256::GetRootCauseDesc() const
{
    return "init_general_slave_devices 在执行初始化前发现调用方传入的 设备 "
           "不满足当前操作要求，通常是对象为空、状态不匹配或与 provider "
           "能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure256::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure256::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure256::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid slave device number of device";
}

std::string UrmaFailure256::GetId() const
{
    return "urma_256";
}

} // namespace diag
