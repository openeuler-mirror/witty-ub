#include "urma_failure_232.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure232> g_urma("urma_232");

bool UrmaFailure232::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("get_topo_info_from_ko") != std::string::npos &&
           message.find("Failed to create topo map") != std::string::npos;
}

std::string UrmaFailure232::GetName() const
{
    return "下层资源创建失败导致获取TOPO、INFO、KO失败";
}

std::string UrmaFailure232::GetRootCauseDesc() const
{
    return "get_topo_info_from_"
           "ko在获取TOPO、INFO、KO过程中依赖下层对象或provider创建结果，下层返回失败后当前资源无法建立。";
}

RootCause UrmaFailure232::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure232::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure232::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：get_topo_info_from_ko，Failed to create topo map。";
}

std::string UrmaFailure232::GetId() const
{
    return "urma_232";
}
} // namespace diag
