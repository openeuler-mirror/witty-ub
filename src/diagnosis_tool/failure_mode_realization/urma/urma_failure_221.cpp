#include "urma_failure_221.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure221> g_urma("urma_221");

bool UrmaFailure221::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'bdp_v_conn_init' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Failed to init slide window in bdp_v_conn_table_add')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure221::GetName() const
{
    return "bdp_v_conn_init 更新 映射表 映射结构失败导致资源索引不可用";
}

std::string UrmaFailure221::GetRootCauseDesc() const
{
    return "bdp_v_conn_init 需要维护 映射表 "
           "到物理资源或虚拟资源的映射关系，但哈希表创建、插入、删除或查找失败，后续无法通过标识定位正确资源。";
}

RootCause UrmaFailure221::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure221::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure221::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to init slide window in bdp_v_conn_table_add";
}

std::string UrmaFailure221::GetId() const
{
    return "urma_221";
}

} // namespace diag
