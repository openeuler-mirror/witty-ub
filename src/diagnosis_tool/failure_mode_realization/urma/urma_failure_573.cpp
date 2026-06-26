#include "urma_failure_573.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure573> g_urma("urma_573");

bool UrmaFailure573::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_free_jfr") != std::string::npos &&
           message.find("jfr still actived, please deactived first") != std::string::npos;
}

std::string UrmaFailure573::GetName() const
{
    return "JFR状态不满足要求导致释放JFR失败";
}

std::string UrmaFailure573::GetRootCauseDesc() const
{
    return "urma_free_jfr执行释放JFR时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure573::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure573::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure573::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_free_jfr，jfr still actived, please deactived first。";
}

std::string UrmaFailure573::GetId() const
{
    return "urma_573";
}
} // namespace diag
