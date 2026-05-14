#include "urma_failure_561.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure561> g_urma("urma_561");

bool UrmaFailure561::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'import_pjetty_for_primary_eid' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Primary dev has NULL ctx')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure561::GetName() const
{
    return "import_pjetty_for_primary_eid 执行导入 context 失败导致当前资源状态无法推进";
}

std::string UrmaFailure561::GetRootCauseDesc() const
{
    return "import_pjetty_for_primary_eid 调用下层 provider、bond 组件或系统接口处理 context 时返回失败，当前分支携带 "
           "ret/errno 等错误结果退出，导致该资源的创建、导入、修改、投递或清理状态无法继续推进。";
}

RootCause UrmaFailure561::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure561::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure561::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Primary dev has NULL ctx";
}

std::string UrmaFailure561::GetId() const
{
    return "urma_561";
}

} // namespace diag
