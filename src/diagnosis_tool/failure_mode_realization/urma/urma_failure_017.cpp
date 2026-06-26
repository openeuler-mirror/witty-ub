#include "urma_failure_017.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure017> g_urma("urma_017");

bool UrmaFailure017::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bdp_v_conn_init") != std::string::npos &&
           message.find("Failed to init slide window in bdp_v_conn_table_add") != std::string::npos;
}

std::string UrmaFailure017::GetName() const
{
    return "初始化BDP、CONN执行失败导致初始化BDP、CONN失败";
}

std::string UrmaFailure017::GetRootCauseDesc() const
{
    return "bdp_v_conn_init执行初始化BDP、CONN时依赖的初始化BDP、CONN步骤返回错误，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure017::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure017::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure017::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bdp_v_conn_init，Failed to init slide window in bdp_v_conn_table_add。";
}

std::string UrmaFailure017::GetId() const
{
    return "urma_017";
}
} // namespace diag
