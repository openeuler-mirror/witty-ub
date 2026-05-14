#include "urma_failure_243.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure243> g_urma("urma_243");

bool UrmaFailure243::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'create_bjetty_ctx' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Unaligned hdr_buf_size')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure243::GetName() const
{
    return "create_bjetty_ctx 执行创建 context 失败导致当前资源状态无法推进";
}

std::string UrmaFailure243::GetRootCauseDesc() const
{
    return "create_bjetty_ctx 调用下层 provider、bond 组件或系统接口处理 context 时返回失败，当前分支携带 ret/errno "
           "等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure243::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure243::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure243::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Unaligned hdr_buf_size";
}

std::string UrmaFailure243::GetId() const
{
    return "urma_243";
}

} // namespace diag
