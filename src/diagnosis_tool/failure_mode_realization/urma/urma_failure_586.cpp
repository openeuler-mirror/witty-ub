#include "urma_failure_586.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure586> g_urma("urma_586");

bool UrmaFailure586::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'urma_cmd_import_seg' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure586::GetName() const
{
    return "urma_cmd_import_seg 校验 context 无效导致导入流程拒绝继续执行";
}

std::string UrmaFailure586::GetRootCauseDesc() const
{
    return "urma_cmd_import_seg 在执行导入前发现调用方传入的 context "
           "不满足当前操作要求，通常是对象为空、状态不匹配或与 provider "
           "能力不一致，因此直接返回错误以避免继续访问非法资源。";
}

RootCause UrmaFailure586::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure586::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure586::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Invalid parameter";
}

std::string UrmaFailure586::GetId() const
{
    return "urma_586";
}

} // namespace diag
