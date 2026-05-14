#include "urma_failure_604.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure604> g_urma("urma_604");

bool UrmaFailure604::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_import_seg' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Token value must be set when token policy is not URMA_TOKEN_NONE')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure604::GetName() const
{
    return "urma_import_seg 执行导入 segment 失败导致当前资源状态无法推进";
}

std::string UrmaFailure604::GetRootCauseDesc() const
{
    return "urma_import_seg 调用下层 provider、bond 组件或系统接口处理 segment 时返回失败，当前分支携带 ret/errno "
           "等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure604::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure604::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure604::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Token value must be set when token policy is not URMA_TOKEN_NONE";
}

std::string UrmaFailure604::GetId() const
{
    return "urma_604";
}

} // namespace diag
