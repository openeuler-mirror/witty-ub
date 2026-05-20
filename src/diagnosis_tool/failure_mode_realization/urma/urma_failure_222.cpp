#include "urma_failure_222.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure222> g_urma("urma_222");

bool UrmaFailure222::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'bdp_v_conn_init' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to init sender slide window in bdp_v_conn_table_add'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure222::GetName() const
{
    return "bdp_v_conn_init 更新 映射表 映射结构失败导致资源索引不可用";
}

std::string UrmaFailure222::GetRootCauseDesc() const
{
    return "bdp_v_conn_init 需要维护 映射表 "
           "到物理资源或虚拟资源的映射关系，但哈希表创建、插入、删除或查找失败，后续无法通过标识定位正确资源。";
}

RootCause UrmaFailure222::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure222::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure222::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to init sender slide window in bdp_v_conn_table_add";
}

std::string UrmaFailure222::GetId() const
{
    return "urma_222";
}

} // namespace diag
