#include "urma_failure_268.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure268> g_urma("urma_268");

bool UrmaFailure268::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_get_net_addr_list") != std::string::npos &&
           message.find("Failed to get netaddr list, ret:") != std::string::npos &&
           message.find(", max_netaddr_cnt:") != std::string::npos;
}

std::string UrmaFailure268::GetName() const
{
    return "下层查询返回失败导致获取NET、ADDR、列表失败";
}

std::string UrmaFailure268::GetRootCauseDesc() const
{
    return "urma_get_net_addr_"
           "list需要从provider、驱动或缓存中获取NET、ADDR、列表状态，查询结果失败会导致调用方无法取得有效信息。";
}

RootCause UrmaFailure268::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure268::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure268::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_get_net_addr_list，Failed to get netaddr list, ret:，, "
           "max_netaddr_cnt:。";
}

std::string UrmaFailure268::GetId() const
{
    return "urma_268";
}
} // namespace diag
