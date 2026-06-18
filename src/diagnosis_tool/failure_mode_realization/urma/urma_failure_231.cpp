#include "urma_failure_231.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure231> g_urma("urma_231");

bool UrmaFailure231::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("get_topo_info_from_ko") != std::string::npos &&
           message.find("Failed to get topo info, change to general mode") != std::string::npos;
}

std::string UrmaFailure231::GetName() const
{
    return "下层查询返回失败导致获取TOPO、INFO、KO失败";
}

std::string UrmaFailure231::GetRootCauseDesc() const
{
    return "get_topo_info_from_"
           "ko需要从provider、驱动或缓存中获取TOPO、INFO、KO状态，查询结果失败会导致调用方无法取得有效信息。";
}

RootCause UrmaFailure231::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure231::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure231::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：get_topo_info_from_ko，Failed to get topo info, change to general "
           "mode。";
}

std::string UrmaFailure231::GetId() const
{
    return "urma_231";
}
} // namespace diag
