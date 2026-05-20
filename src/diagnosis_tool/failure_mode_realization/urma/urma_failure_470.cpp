#include "urma_failure_470.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure470> g_urma("urma_470");

bool UrmaFailure470::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'urma_register_seg' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F '[DRV_ERR]register seg failed, dev_name:' | "
        "grep -F ', eid_idx:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure470::GetName() const
{
    return "urma_register_seg 校验 context 无效导致注册流程拒绝继续执行";
}

std::string UrmaFailure470::GetRootCauseDesc() const
{
    return "urma_register_seg 在执行注册前发现调用方传入的 context 不满足当前操作要求，通常是对象为空、状态不匹配或与 "
           "provider 能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure470::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure470::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure470::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：[DRV_ERR]register seg failed, dev_name: , eid_idx";
}

std::string UrmaFailure470::GetId() const
{
    return "urma_470";
}

} // namespace diag
