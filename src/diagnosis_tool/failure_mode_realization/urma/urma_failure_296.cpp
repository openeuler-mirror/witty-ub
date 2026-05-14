#include "urma_failure_296.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure296> g_urma("urma_296");

bool UrmaFailure296::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'deepcopy_faa_wr' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Failed to alloc new_wr_faa->dst')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure296::GetName() const
{
    return "deepcopy_faa_wr 分配 WR 临时参数失败导致复制流程无法继续";
}

std::string UrmaFailure296::GetRootCauseDesc() const
{
    return "deepcopy_faa_wr 需要为 WR 构造命令参数、资源描述或临时缓存，但内存分配返回失败，后续 provider "
           "调用或驱动命令缺少必要入参，因此当前 URMA 操作被阻断。";
}

RootCause UrmaFailure296::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure296::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure296::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to alloc new_wr_faa->dst";
}

std::string UrmaFailure296::GetId() const
{
    return "urma_296";
}

} // namespace diag
