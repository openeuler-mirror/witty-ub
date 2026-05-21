#include "urma_failure_607.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure607> g_urma("urma_607");

bool UrmaFailure607::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'urma_unimport_seg' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure607::GetName() const
{
    return "urma_unimport_seg 校验 目标 segment 无效导致导入流程拒绝继续执行";
}

std::string UrmaFailure607::GetRootCauseDesc() const
{
    return "urma_unimport_seg 在执行导入前发现调用方传入的 目标 segment "
           "不满足当前操作要求，通常是对象为空、状态不匹配或与 provider "
           "能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure607::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure607::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure607::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid parameter";
}

std::string UrmaFailure607::GetId() const
{
    return "urma_607";
}

} // namespace diag
