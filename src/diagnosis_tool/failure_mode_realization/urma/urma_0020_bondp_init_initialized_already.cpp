#include "urma_0020_bondp_init_initialized_already.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0020BondpInitInitializedAlready> g_urma("urma_0020");

bool Urma0020BondpInitInitializedAlready::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Initialized already"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0020BondpInitInitializedAlready::GetName() const
{
    return "bondp_init Initialized already";
}

std::string Urma0020BondpInitInitializedAlready::GetRootCauseDesc() const
{
    return "读取 sysfs 或设备文件失败，可能由于设备未注册、路径不存在、权限不足或读取返回异常；该路径返回 URMA_FAIL";
}

RootCause Urma0020BondpInitInitializedAlready::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0020BondpInitInitializedAlready::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0020BondpInitInitializedAlready::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Initialized already";
}

std::string Urma0020BondpInitInitializedAlready::GetId() const
{
    return "urma_0020";
}
} // namespace diag
