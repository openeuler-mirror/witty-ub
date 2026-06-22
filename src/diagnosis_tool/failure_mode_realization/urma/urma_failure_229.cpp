#include "urma_failure_229.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure229> g_urma("urma_229");

bool UrmaFailure229::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("get_comp_by_cr") != std::string::npos &&
           message.find("Failed to get comp, local_id:") != std::string::npos;
}

std::string UrmaFailure229::GetName() const
{
    return "下层查询返回失败导致获取COMP、CR失败";
}

std::string UrmaFailure229::GetRootCauseDesc() const
{
    return "get_comp_by_cr需要从provider、驱动或缓存中获取COMP、CR状态，查询结果失败会导致调用方无法取得有效信息。";
}

RootCause UrmaFailure229::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure229::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure229::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：get_comp_by_cr，Failed to get comp, local_id:。";
}

std::string UrmaFailure229::GetId() const
{
    return "urma_229";
}
} // namespace diag
