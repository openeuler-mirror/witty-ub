#include "urma_failure_892.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure892> g_urma("urma_892");

bool UrmaFailure892::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_check_seg_cfg' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Local only access is not allowed to config with other accesses')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure892::GetName() const
{
    return "urma_check_seg_cfg 执行校验 segment 失败导致当前资源状态无法推进";
}

std::string UrmaFailure892::GetRootCauseDesc() const
{
    return "urma_check_seg_cfg 调用下层 provider、bond 组件或系统接口处理 segment 时返回失败，当前分支携带 ret/errno "
           "等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure892::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure892::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure892::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Local only access is not allowed to config with other accesses";
}

std::string UrmaFailure892::GetId() const
{
    return "urma_892";
}

} // namespace diag
